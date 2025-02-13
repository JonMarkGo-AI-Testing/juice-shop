/*
 * Copyright (c) 2014-2024 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import challengeUtils = require('../lib/challengeUtils')
import { type Request, type Response, type NextFunction } from 'express'
import { type Review } from '../data/types'
import * as db from '../data/mongodb'
import { challenges } from '../data/datacache'
import { ObjectId } from 'mongodb'

const security = require('../lib/insecurity')

module.exports = function productReviews () {
  return (req: Request, res: Response, next: NextFunction) => {
    let reviewId: ObjectId
    try {
      reviewId = new ObjectId(req.body.id)
    } catch (e) {
      return res.status(400).json({ error: 'Invalid review ID format' })
    }
    const user = security.authenticatedUsers.from(req)
    db.reviewsCollection.findOne({ _id: reviewId }, { projection: { _id: 1, likedBy: 1 } }).then((review: Review) => {
      if (!review) {
        res.status(404).json({ error: 'Not found' })
      } else {
        const likedBy = review.likedBy || []
        if (!likedBy.includes(user.data.email)) {
          db.reviewsCollection.updateOne(
            { _id: reviewId },
            { 
              $inc: { likesCount: 1 },
              $addToSet: { likedBy: user.data.email }
            }
          ).then(
            () => {
              // Artificial wait for timing attack challenge
              setTimeout(function () {
                db.reviewsCollection.findOne({ _id: reviewId }, { projection: { likedBy: 1 } }).then((review: Review) => {
                  const count = (review?.likedBy || []).filter(email => email === user.data.email).length
                  challengeUtils.solveIf(challenges.timingAttackChallenge, () => { return count > 2 })
                  res.json({ status: 'success' })
                }, (err: unknown) => {
                  res.status(500).json(err)
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
