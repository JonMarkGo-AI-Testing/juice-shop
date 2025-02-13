/*
 * Copyright (c) 2014-2024 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import challengeUtils = require('../lib/challengeUtils')
import { type Request, type Response, type NextFunction } from 'express'
import { type Review } from '../data/types'
import * as db from '../data/mongodb'
import { challenges } from '../data/datacache'

const security = require('../lib/insecurity')

module.exports = function productReviews () {
  return (req: Request, res: Response, next: NextFunction) => {
    const id = req.body.id
    // Validate id is a string and meets expected format
    if (typeof id !== 'string' || !id.match(/^[a-zA-Z0-9-_]+$/)) {
      return res.status(400).json({ error: 'Invalid review ID format' })
    }
    const user = security.authenticatedUsers.from(req)
    db.reviewsCollection.findOne({ _id: id.toString() }).then((review: Review) => {
      if (!review) {
        res.status(404).json({ error: 'Not found' })
      } else {
        const likedBy = review.likedBy
        if (!likedBy.includes(user.data.email)) {
          db.reviewsCollection.update(
            { _id: id.toString() },
            { $inc: { likesCount: 1 } },
            { multi: false } // Ensure only one document is updated
          ).then(
            () => {
              // Artificial wait for timing attack challenge
              setTimeout(function () {
                db.reviewsCollection.findOne({ _id: id.toString() }).then((review: Review) => {
                  const likedBy = review.likedBy
                  likedBy.push(user.data.email)
                  let count = 0
                  for (let i = 0; i < likedBy.length; i++) {
                    if (likedBy[i] === user.data.email) {
                      count++
                    }
                  }
                  challengeUtils.solveIf(challenges.timingAttackChallenge, () => { return count > 2 })
                  db.reviewsCollection.update(
                    { _id: id.toString() },
                    { $set: { likedBy: likedBy.filter(email => typeof email === 'string') } },
                    { multi: false } // Ensure only one document is updated
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
