/*
 * Copyright (c) 2014-2024 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import * as challengeUtils from '../lib/challengeUtils'
import { type Request, type Response, type NextFunction } from 'express'
import { type Review } from '../data/types'
import * as db from '../data/mongodb'
import { challenges } from '../data/datacache'
import { ObjectId as MongoObjectId } from 'mongodb'

import * as security from '../lib/insecurity'

export default function productReviews () {
  return (req: Request, res: Response, next: NextFunction) => {
    let id: string
    try {
      if (!req.body.id || typeof req.body.id !== 'string') {
        throw new Error('Invalid id parameter')
      }
      id = new MongoObjectId(req.body.id).toHexString()
    } catch (error) {
      return res.status(400).json({ error: 'Invalid review ID format' })
    }

    const user = security.authenticatedUsers.from(req)
    if (!user?.data?.email) {
      return res.status(401).json({ error: 'Authentication required' })
    }

    db.reviewsCollection.findOne(
      { _id: new MongoObjectId(id) },
      { projection: { likedBy: 1, likesCount: 1 } }
    ).then((review: Review) => {
      if (!review) {
        res.status(404).json({ error: 'Not found' })
      } else {
        const likedBy = review.likedBy
        if (!likedBy.includes(user.data.email)) {
          db.reviewsCollection.updateOne(
            { _id: new MongoObjectId(id) },
            { $inc: { likesCount: 1 } },
            { runValidators: true, upsert: false }
          ).then(
            () => {
              // Artificial wait for timing attack challenge
              setTimeout(function () {
                db.reviewsCollection.findOne(
                  { _id: new MongoObjectId(id) },
                  { projection: { likedBy: 1, likesCount: 1 } }
                ).then((review: Review) => {
                  if (!review?.likedBy) {
                    return res.status(400).json({ error: 'Invalid review data' })
                  }
                  const likedBy = review.likedBy
                  const userEmail = user.data.email
                  likedBy.push(userEmail)
                  let count = 0
                  for (let i = 0; i < likedBy.length; i++) {
                    if (likedBy[i] === userEmail) {
                      count++
                    }
                  }
                  challengeUtils.solveIf(challenges.timingAttackChallenge, () => { return count > 2 })
                  db.reviewsCollection.updateOne(
                    { _id: new MongoObjectId(id) },
                    { $set: { likedBy: likedBy.map(email => String(email)) } },
                    { runValidators: true, upsert: false }
                  ).then(
                    (result: any) => {
                      res.json(result)
                    }, (err: unknown) => {
                      res.status(500).json(err)
                    })
                }, () => {
                  res.status(400).json({ error: 'Wrong Params' })
                })
              }, 150)
            }, (err: unknown) => {
              res.status(500).json(err)
            })
        } else {
          res.status(403).json({ error: 'Not allowed' })
        }
      }
    }, () => {
      res.status(400).json({ error: 'Wrong Params' })
    })
  }
}
